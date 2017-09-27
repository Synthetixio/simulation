pragma solidity ^0.4.11;

/*    - Prefer exceptions to return values. (Too paranoid?)
 *    - Check things before execution, rather than afterwards and revert, if possible.
 *    - Need to work out how the fixed-precision arithmetic should go.
 *    - When and how frequently are fees distributed? (and How?)
 */


contract PriceOracle {
    uint decimals = 18;
    // Prices of dollars in tokens (t/$). e.g. 100 curits / 10 curits/$ = $100
    uint curitPrice = 1 * 10**decimals;   // <------  This can float.
    uint nominPrice = 10 * 10**decimals;  // <------- This should not change.
    address admin;

    function PriceOracle() {
        admin = msg.sender;
    }

    function setCuritPrice(uint price) {
        require(msg.sender == admin);
        curitPrice = price;
    }

    function setNominPrice(uint price) {
        require(msg.sender == admin);
        nominPrice = price;
    }

    // TODO: Fill this up so that it converts to the maximum possible number of curits and gives back the unconvertible change.
    // Take nomins in, return the converted quantity of curits and return a residue that was unconvertible.
    // 0 in 0 out.
    function toCurits(uint nomins) public constant returns (uint convertedCur, uint convertedNom) {
        require(nominPrice != 0 && curitPrice != 0);
        
        // For now, just do the naive thing and leak nomins.
        return ((nomins * curitPrice) / nominPrice, 0);
    }
    function toNomins(uint curits) public constant returns (uint convertedCur, uint convertedNom) {
        return (0, (curits * nominPrice) / curitPrice);
    }
}

contract ERC20Token {
    // Get the total token supply
    function totalSupply() constant returns (uint totalSupply);
 
    // Get the account balance of another account with address _owner
    function balanceOf(address _owner) constant returns (uint balance);
 
    // Send _value amount of tokens to address _to
    function transfer(address _to, uint _value) returns (bool success);
 
    // Send _value amount of tokens from address _from to address _to
    function transferFrom(address _from, address _to, uint _value) returns (bool success);
  
    // Allow _spender to withdraw from your account, multiple times, up to the _value amount.
    // If this function is called again it overwrites the current allowance with _value.
    // this function is required for some DEX functionality
    function approve(address _spender, uint _value) returns (bool success);
 
    // Returns the amount which _spender is still allowed to withdraw from _owner
    function allowance(address _owner, address _spender) constant returns (uint remaining);
 
    // Triggered when tokens are transferred.
    event Transfer(address indexed _from, address indexed _to, uint _value);
 
    // Triggered whenever approve(address _spender, uint _value) is called.
    event Approval(address indexed _owner, address indexed _spender, uint _value);
}

contract Curit is ERC20Token {
    string public constant name = "Curit";
    string public constant symbol = "CUR";
    uint public constant decimals = 18;

    // Token parameters
    uint public transferFeeRate = 1000; // Reciprocal = 0.1%
    uint public minimumFee = 100;       // Charge at least this much so no free transactions.
    // Note, a minimum fee entails a minimum transferrable balance.

    // A person may issue at most (1/utilisationRatio)*(escrowed curits) value of nomins
    uint utilisationRatio = 5;

    // Total supply of Curits is static.
    uint supply = 1000000000;

    // All curit balances and owner-approved transfers.
    // Invariant: Sum_i of {balances[i] + Sum_j of approved[i][j]} = supply
    // Balances are straightforward. 
    // Approved-withdrawal accounts require an owner to transfer curits to someone's
    // address in the approved map. Requiring a transfer is better than
    // distributing drawing rights since it may be possible to get into
    // a situation where the aggregate drawing rights allocated by someone
    // exceed their available balance, at which time they can't service their debt.
    // The contract's own pool of curits is stored at balances[this].
    mapping(address => uint) balances;
    mapping(address => mapping(address => uint)) approved;

    // The quantity of Curits each account has escrowed in order to issue Nomins
    // Invariant: Sum_i of escrowedCurits[i] <= suuply
    mapping(address => uint) escrowedCurits;
    // The total nomins issued by a given address;
    mapping(address => uint) issuedNomins;

    // Price oracle
    PriceOracle oracle;
    // Nomin contract
    Nomin nominContract;

    // Admin address for updating the oracle, nomin contract.
    address admin;

    function Curit() {
        admin = msg.sender;
    }

    function setOracle(PriceOracle newOracle) {
        oracle = newOracle;
    }

    function setNominContract(Nomin newNominContract) {
        nominContract = newNominContract;
    }

    // Total value of curits that can have nomins issued against them.
    function issuableValue() constant internal returns (uint) {
        return escrowedCurits[msg.sender] / utilisationRatio;
    }

    // Total value of nomins issuable.
    function issuable() constant internal returns (uint) {
        var (c, n) = oracle.toNomins(issuableValue());
        return n;
    }

    // Remaining issuable nomins.
    function remainingIssuable() constant internal returns (uint) {
        var i = issuable();
        var iN = issuedNomins[msg.sender];
        if (i < iN) {
            return 0;
        }
        return i - iN;
    }

    function remainingIssuableValue() constant internal returns (uint) {
        var (c, n) = oracle.toCurits(remainingIssuable());
        return c;
    }

    function escrowCurits(uint value) returns (bool) {
        uint bp = balances[msg.sender];
        uint be = escrowedCurits[msg.sender];
        require(bp >= value);
        balances[msg.sender] -= value;
        escrowedCurits[msg.sender] += value;
        require(bp + be == balances[msg.sender] + escrowedCurits[msg.sender]);
        return true;
    }

    // Redeem curits previously escrowed, up to the amount allowed by issued nomins and
    // the utilisation ratio.
    function redeemCurits(uint value) returns (bool) {
        uint bp = balances[msg.sender];
        uint be = escrowedCurits[msg.sender];
        uint rV = remainingIssuableValue();
        // TODO: check what the result of signed-unsigned comparisons are.
        require(rV >= value);
        require(be >= value);
        escrowedCurits[msg.sender] -= value;
        balances[msg.sender] += value;
        require(bp + be == balances[msg.sender] + escrowedCurits[msg.sender]);
        return true;
    }


    function issueNomins(uint nomins) returns (bool) {
        // Must have enough issuing rights
        uint rI = remainingIssuable();
        require(rI >= nomins);
        issuedNomins[msg.sender] += nomins;
        nominContract.issue(msg.sender, nomins);
        return true;
    }

    function transferFee(uint value) constant internal returns (uint) {
        uint fee = value / transferFeeRate; 
        return fee < minimumFee ? minimumFee : fee;
    }

    // The maximum number of nomins that 
    function maxIssuance() constant internal returns (uint) {

    }

    function totalSupply() constant returns (uint) { 
        return supply;
    }

    function pool() constant returns (uint) {
        return balances[this];
    }

    function balanceOf(address account) constant returns (uint) {
        return balances[account];
    }
   
    // Precondition: there is enough balance to cover the value + fee
    // Postcondition: die if the total number of curits changed
    // in an interaction between two accounts, including by overflows.
    // We assume that the value being transferred is non-negative.
    function transfer(address to, uint value) returns (bool) {
        // Precondition check: sufficient balance + overflow
        uint fee = transferFee(value);
        uint bf = balances[msg.sender];
        uint bp = balances[this];
        uint bt = balances[to];
        require((fee + value) <= bf);
        require(bf >= bf - (fee + value));
        require(bp <= bp + fee);
        require(bt <= bt + value);

        // Perform the actual transfer
        balances[msg.sender] = bf - (fee + value);
        balances[this] = bp + fee;
        balances[to] = bt + value;
        Transfer(msg.sender, to, value);
        Transfer(msg.sender, this, fee);

        // Postcondition: sum of balances remains the same
        // so no money was lost anywhere (overkill?)
        require(bf + bp + bt == balances[msg.sender] + balances[this] + balances[to]);
        return true;
    }
    
    // Precondition: the from address is authorised to make the transfer, and there is enough balance for it
    // Postcondition: sum of balances remains the same
    function transferFrom(address from, address to, uint value) returns (bool success) {
        // Precondition check: sufficient authorised balance check + overflows
        uint fee = transferFee(value);
        uint bf = approved[from][msg.sender];
        uint bp = balances[this];
        uint bt = balances[to];
        require((fee + value) <= bf);
        require(bf >= bf - (fee + value));
        require(bp <= bp + fee);
        require(bt <= bt + value);

        // Perform the actual transfer
        approved[from][msg.sender] = bf - (fee + value);
        balances[this] = bp + fee;
        balances[to] = bt + value;
        Transfer(from, to, value);
        Transfer(from, this, fee);

        // No money was lost anywhere
        require(bf + bp + bt == approved[from][msg.sender] + balances[this] + balances[to]);
        return true;
    }


    function approve(address delegate, uint value) returns (bool success) {
        uint preAllowance = approved[msg.sender][delegate];
        uint balance = balances[msg.sender];
        uint margin;

        if (value > preAllowance) {
        // If the desired allowance exceeds the current one, it must be increased.
            margin = value - preAllowance;

            // There needs to be enough money to send, and check for overflows
            require(margin <= balance);
            require(balance >= balance - margin);
            require(preAllowance <= preAllowance + margin);

            // Increase the allowance.
            balances[msg.sender] = balance - margin;
            approved[msg.sender][delegate] = preAllowance + margin;

        } else {
        // Otherwise it needs to be reduced
            margin = preAllowance - value;

            // Check for overflows
            require(balance <= balance + margin);
            require(preAllowance >= preAllowance - margin);

            // Decrease the allowance and remit the difference to the owner.
            approved[msg.sender][delegate] = preAllowance - margin;
            balances[msg.sender] += margin;
        }

        require(approved[msg.sender][delegate] == value);
        require(preAllowance + balance == approved[msg.sender][delegate] + balances[msg.sender]);
        return true;
    }
 
    // Returns the amount which _spender is still allowed to withdraw from _owner
    function allowance(address owner, address spender) constant returns (uint remaining) {
        return approved[owner][spender];
    }
}



contract Nomin is ERC20Token {
    string public constant name = "Nomin";
    string public constant symbol = "NOM";
    uint public constant decimals = 18;

    // Token parameters
    uint public transferFeeRate = 1000; // Reciprocal = 0.1%
    uint public minimumFee = 100;       // Charge at least this much so no free transactions.
    // Note, a minimum fee entails a minimum transferrable balance.

    // Any time nomins are issued or burnt, this quantity should update.
    uint supply = 0;

    // All nomin balances and owner-approved transfers.
    // Invariant: Sum_i of {balances[i] + Sum_j of approved[i][j]} = supply
    // Balances are straightforward. 
    // Approved-withdrawal accounts require an owner to transfer nomins to someone's
    // address in the approved map. Requiring a transfer is better than
    // distributing drawing rights since it may be possible to get into
    // a situation where the aggregate drawing rights allocated by someone
    // exceed their available balance, at which time they can't service their debt.
    // The contract's own pool of nomins is stored at balances[this].
    mapping(address => uint) balances;
    mapping(address => mapping(address => uint)) approved;

    // Price oracle
    PriceOracle oracle;
    // Curit contract
    Curit curitContract;

    // Admin address for updating the oracle, curit contract.
    address admin;

    function Nomin() {
        admin = msg.sender;
    }

    function setOracle(PriceOracle newOracle) {
        oracle = newOracle;
    }

    function setCuritContract(Curit newCuritContract) {
        curitContract = newCuritContract;
    }

    function transferFee(uint value) constant internal returns (uint) {
        uint fee = value / transferFeeRate; 
        return fee < minimumFee ? minimumFee : fee;
    }

    function totalSupply() constant returns (uint totalSupply) { 
        return supply;
    }

    function pool() constant returns (uint feePool) {
        return balances[this];
    }


    // Should only be executed after checks that the right to issue the desired value is granted.
    function issue(address account, uint value) returns (bool success) {
        require(msg.sender == address(curitContract));
        balances[account] += value;
        supply += value;
        return true;
    }

    // Should only be executed after checks that the right to burn the desired value is granted.
    function burn(address account, uint value) returns (bool success) {
        // Ensure the balance is high enough.
        require(msg.sender == address(curitContract));
        require(balances[account] >= value);
        balances[account] -= value;
        supply -= value;
        return true;
        
    }

    function balanceOf(address account) constant returns (uint balance) {
        return balances[account];
    }
   
    // Precondition: there is enough balance to cover the value + fee
    // Postcondition: die if the total number of nomins changed
    // in an interaction between two accounts, including by overflows.
    // We assume that the value being transferred is non-negative.
    function transfer(address to, uint value) returns (bool success) {
        // Precondition check: sufficient balance + overflow
        uint fee = transferFee(value);
        uint bf = balances[msg.sender];
        uint bp = balances[this];
        uint bt = balances[to];
        require((fee + value) <= bf);
        require(bf >= bf - (fee + value));
        require(bp <= bp + fee);
        require(bt <= bt + value);

        // Perform the actual transfer
        balances[msg.sender] = bf - (fee + value);
        balances[this] = bp + fee;
        balances[to] = bt + value;
        Transfer(msg.sender, to, value);
        Transfer(msg.sender, this, fee);

        // Postcondition: sum of balances remains the same
        // so no money was lost anywhere (overkill?)
        require(bf + bp + bt == balances[msg.sender] + balances[this] + balances[to]);
        return true;
    }
    
    // Precondition: the from address is authorised to make the transfer, and there is enough balance for it
    // Postcondition: sum of balances remains the same
    function transferFrom(address from, address to, uint value) returns (bool success) {
        // Precondition check: sufficient authorised balance check + overflows
        uint fee = transferFee(value);
        uint bf = approved[from][msg.sender];
        uint bp = balances[this];
        uint bt = balances[to];
        require((fee + value) <= bf);
        require(bf >= bf - (fee + value));
        require(bp <= bp + fee);
        require(bt <= bt + value);

        // Perform the actual transfer
        approved[from][msg.sender] = bf - (fee + value);
        balances[this] = bp + fee;
        balances[to] = bt + value;
        Transfer(from, to, value);
        Transfer(from, this, fee);

        // No money was lost anywhere
        require(bf + bp + bt == approved[from][msg.sender] + balances[this] + balances[to]);
        return true;
    }


    function approve(address delegate, uint value) returns (bool success) {
        uint preAllowance = approved[msg.sender][delegate];
        uint balance = balances[msg.sender];
        uint margin;

        if (value > preAllowance) {
        // If the desired allowance exceeds the current one, it must be increased.
            margin = value - preAllowance;

            // There needs to be enough money to send, and check for overflows
            require(margin <= balance);
            require(balance >= balance - margin);
            require(preAllowance <= preAllowance + margin);

            // Increase the allowance.
            balances[msg.sender] = balance - margin;
            approved[msg.sender][delegate] = preAllowance + margin;

        } else {
        // Otherwise it needs to be reduced
            margin = preAllowance - value;

            // Check for overflows
            require(balance <= balance + margin);
            require(preAllowance >= preAllowance - margin);

            // Decrease the allowance and remit the difference to the owner.
            approved[msg.sender][delegate] = preAllowance - margin;
            balances[msg.sender] += margin;
        }

        require(approved[msg.sender][delegate] == value);
        require(preAllowance + balance == approved[msg.sender][delegate] + balances[msg.sender]);
        return true;
    }
 
    // Returns the amount which _spender is still allowed to withdraw from _owner
    function allowance(address owner, address spender) constant returns (uint remaining) {
        return approved[owner][spender];
    }
}